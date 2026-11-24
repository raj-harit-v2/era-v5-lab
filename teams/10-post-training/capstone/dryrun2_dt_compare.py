"""Matched-step DT vs LoRA vs full fine-tuning comparison on a Team 5 dry run 2 checkpoint.

Runs three equal-step SFT arms on the same checkpoint, slice (A2 or A4), seed, and evaluation screens:
  1. full   --method full --lr <full_lr>               (measures base once; sets completed step budget)
  2. lora   --method lora --lr <lora_lr> --marker-rows (exact same completed steps; --no-before)
  3. dt     --method dt   --lr <dt_lr>   --marker-rows (17 Nov paper-repo DT settings; exact same steps; --no-before)

Optional weight retention (both default off):
  --keep-canary-state-dir DIR   copies the DT arm's model.safetensors, dt_keep_masks.bin, dt_keep_masks.bin.json
                                + SHA256SUMS to DIR/dt/ for the Task 11 DT-then-RL canary before cleanup.
  --keep-weights-dir DIR        writes Team 7 Checkpointer run folders (for Team 9's watcher) for arms named by
                                --keep-weights-arms (comma-separated subset of full,lora,dt).

Outputs: out/pins.json, out/inputs.json, out/sft_{full,lora,dt}.json, out/compare.json, out/compare.md, out/summary.json.
Training rows (out/_inputs) and unkept weights/generations are always removed on exit.
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
import sft_job_v1 as job  # noqa: E402

ARMS = ("full", "lora", "dt")
AT_LIMIT_MARGIN_BPB = 0.01


def build_arm_cmd(a, arm: str, cfg: Path, rows: Path, dev: Path, arm_out: Path, steps: int,
                  no_before: bool) -> list[str]:
    if arm == "full":
        method = ["--method", "full", "--lr", str(a.full_lr)]
    elif arm == "lora":
        method = ["--method", "lora", "--lr", str(a.lora_lr), "--marker-rows", "--wd", "0",
                  "--marker-lr", str(a.marker_lr), "--lora-r", str(a.lora_r), "--lora-alpha", str(a.lora_alpha)]
    elif arm == "dt":
        method = ["--method", "dt", "--lr", str(a.dt_lr), "--marker-rows", "--wd", "0",
                  "--marker-lr", str(a.marker_lr), "--dt-targets", a.dt_targets,
                  "--dt-alpha-start", str(a.dt_alpha_start), "--dt-alpha-end", str(a.dt_alpha_end),
                  "--dt-lambda", str(a.dt_lambda), "--dt-eta", str(a.dt_eta),
                  "--dt-prior-strength", str(a.dt_prior_strength), "--dt-unseen", a.dt_unseen,
                  "--dt-calib-rows", str(a.dt_calib_rows)]
    else:
        raise ValueError(f"unknown arm {arm!r}")

    keep_arms = {x.strip() for x in (a.keep_weights_arms or "").split(",") if x.strip()}
    keep_flags = (["--keep-weights-dir", str(a.keep_weights_dir), "--keep-weights-id", f"g10-dr2-{arm}"]
                  if a.keep_weights_dir and arm in keep_arms else [])
    return [
        sys.executable, str(HERE / "sft_g5.py"), "--adapter-config", str(cfg), "--train", str(rows),
        "--eval", str(dev), *method, "--steps", str(steps), "--batch", str(a.batch),
        "--max-train-seconds", str(a.max_train_seconds), "--device", a.device, "--seed", str(a.seed),
        "--gen-limit", str(a.gen_limit), "--gen-max-new", str(a.gen_max_new), "--gen-seconds", str(a.gen_seconds),
        "--heldout", str(a.heldout),
        *(["--heldout-sources", str(a.heldout_sources)] if a.heldout_sources else []),
        *(["--rl-tasks", str(a.rl_tasks), "--rl-ids", str(a.rl_ids), "--rl-max-new", str(a.rl_max_new),
           "--rl-limit", str(a.rl_limit), "--rl-k", str(a.rl_k),
           "--rl-seconds", str(a.rl_seconds)] if a.rl_tasks and a.rl_ids else []),
        *(["--no-before"] if no_before else []),
        *keep_flags,
        "--out", str(arm_out),
    ]


def _forgetting_tag(delta_bpb: float | None) -> str:
    if delta_bpb is None:
        return "n/a"
    verdict = "FORGET" if delta_bpb > job.FORGET_LIMIT_BPB else "ok"
    near = abs(delta_bpb - job.FORGET_LIMIT_BPB) <= AT_LIMIT_MARGIN_BPB + 1e-9
    return f"{verdict} (at limit)" if near else verdict


def summarise_comparison(reps: dict[str, dict], before: dict | None) -> tuple[dict, str]:
    present = [arm for arm in ARMS if arm in reps]
    afters = [reps[arm].get("after") or {} for arm in present]
    gen_ids = job.common_prefix([x.get("generation") for x in afters], "per_row")
    rl_ids = job.common_prefix([x.get("rl_screen") for x in afters], "per_prompt")
    arms_out: dict[str, dict] = {}
    for arm in present:
        rep = reps[arm]
        m = job.arm_metrics(rep, before or rep.get("before"), gen_ids, rl_ids)
        after = rep.get("after") or {}
        m["eval_nll"] = (after.get("eval_loss") or {}).get("nll_per_target")
        m["forgetting_verdict"] = _forgetting_tag(m.get("forgetting_delta_bpb"))
        if arm == "dt":
            mi = rep.get("method_info") or {}
            m["dt_band_at_init"] = mi.get("band_at_init")
            m["dt_deletion_final"] = mi.get("deletion_final")
        arms_out[arm] = m

    steps_set = {arms_out[arm]["steps"] for arm in present}
    base = before or (reps[present[0]].get("before") if present else {}) or {}
    base_summary = {
        "eval_nll": (base.get("eval_loss") or {}).get("nll_per_target"),
        "forgetting": base.get("forgetting"),
        **job.screen_metrics(base.get("generation"), base.get("rl_screen"), gen_ids, rl_ids),
    }
    comp = {
        "arms": arms_out,
        "steps_matched": len(steps_set) == 1,
        "compared_on": {"format_rows": None if gen_ids is None else len(gen_ids),
                        "rl_prompts": None if rl_ids is None else len(rl_ids)},
        "base": base_summary,
        "forgetting_limit_bpb": job.FORGET_LIMIT_BPB,
        "at_limit_margin_bpb": AT_LIMIT_MARGIN_BPB,
    }
    lines = [
        "# Dry Run 2 SFT Comparison: Full FT vs LoRA vs Deletion Tuning",
        "",
        f"Steps matched: `{comp['steps_matched']}` | Forgetting limit: `+{job.FORGET_LIMIT_BPB}` bpb (at-limit margin `±{AT_LIMIT_MARGIN_BPB}`)",
        "",
        "| Arm | Steps | Eval NLL ↓ | Forgetting Δbpb ↓ | Verdict | Format Valid ↑ | Closed Turns ↑ | RL Mixed / Pass |",
        "|---|---:|---:|---:|---|---:|---:|---|",
    ]
    def _fmt(v, fmt=".4f"):
        return "—" if v is None else format(v, fmt)

    lines.append(
        f"| base | 0 | {_fmt(base_summary.get('eval_nll'))} | +0.0000 | base | "
        f"{_fmt(base_summary.get('format_validity'), '.3f')} | {_fmt(base_summary.get('closed_im_end'), '.3f')} | "
        f"{base_summary.get('rl_mixed_groups', '—')} / {_fmt(base_summary.get('rl_pass_rate'), '.3f')} |"
    )
    for arm in present:
        m = arms_out[arm]
        dbpb = "—" if m.get("forgetting_delta_bpb") is None else f"{m['forgetting_delta_bpb']:+.4f}"
        lines.append(
            f"| {arm} | {m.get('steps', '—')} | {_fmt(m.get('eval_nll'))} | {dbpb} | {m['forgetting_verdict']} | "
            f"{_fmt(m.get('format_validity'), '.3f')} | {_fmt(m.get('closed_im_end'), '.3f')} | "
            f"{m.get('rl_mixed_groups', '—')} / {_fmt(m.get('rl_pass_rate'), '.3f')} |"
        )
    return comp, "\n".join(lines) + "\n"


def run(a, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    t_end = time.monotonic() + a.deadline_minutes * 60 if a.deadline_minutes else None

    def left() -> float | None:
        return None if t_end is None else t_end - time.monotonic()

    results = {"pins": probe.step(out, "pins", lambda: {
        **probe.check_pins(a.run_folder, a.tokenizer, a.byte_table),
        **job.check_run_and_inputs(a),
        **job.check_g5_sources(a),
    })}
    if not results["pins"]["ok"]:
        return probe.finish(out, results)

    from make_adapter_config import load_probe, write_config  # noqa: PLC0415
    cfg = write_config(out / "adapter.yaml", a.g5_root, a.run_folder, a.tokenizer, a.byte_table,
                       TEAM10, a.origin, not a.no_git, probe=load_probe(a.probe_file) if a.probe_file else None)
    inp = out / "_inputs"

    def inputs():
        import sft_slice_v1  # noqa: PLC0415
        return sft_slice_v1.build(a.packs, a.tokenizer, a.byte_table, a.max_tokens, inp, a.dev_rows,
                                  check_hashes=not a.no_pack_check)

    results["inputs"] = probe.step(out, "inputs", inputs)
    if not results["inputs"]["ok"]:
        return probe.finish(out, results)

    rows = inp / f"{a.slice_arm}_train.jsonl"
    dev = inp / "dev.jsonl"

    # Arm 1 (full): measures base once and sets matched step count.
    results["sft_full"] = probe.step(out, "sft_full", lambda: job.run_arm(
        out, "full", build_arm_cmd(a, "full", cfg, rows, dev, out / "sft_full", a.steps, False), left()))
    full_res = results["sft_full"]
    matched_steps = full_res.get("steps_completed") or a.steps
    before = full_res.get("before") if full_res["ok"] else None

    # Arm 2 (lora): exact same step budget, skip redundant base eval if full succeeded.
    results["sft_lora"] = probe.step(out, "sft_lora", lambda: job.run_arm(
        out, "lora", build_arm_cmd(a, "lora", cfg, rows, dev, out / "sft_lora", matched_steps, before is not None),
        left()))

    # Arm 3 (dt): 17 Nov paper-repo settings, exact same step budget; optionally keeps canary files for Task 11 RL.
    canary_dest = (a.keep_canary_state_dir / "dt") if a.keep_canary_state_dir else None
    results["sft_dt"] = probe.step(out, "sft_dt", lambda: job.run_arm(
        out, "dt", build_arm_cmd(a, "dt", cfg, rows, dev, out / "sft_dt", matched_steps, before is not None),
        left(), canary_dest=canary_dest))

    def compare():
        reps = {arm: json.loads((out / f"sft_{arm}" / "sft_report.json").read_text(encoding="utf-8"))
                for arm in ARMS if results[f"sft_{arm}"]["ok"]}
        if len(reps) < 3:
            raise RuntimeError(f"only {sorted(reps)} finished; expected all three arms {list(ARMS)}")
        comp, md = summarise_comparison(reps, before)
        (out / "compare.md").write_text(md, encoding="utf-8")
        return comp

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
    ap.add_argument("--packs", type=Path, nargs="+", required=True)
    ap.add_argument("--probe-file", type=Path, default=None, help="optional probe expectation JSON for g5_delivery")
    ap.add_argument("--slice-arm", choices=("a2", "a4"), default="a4", help="OCR-2 slice shape picked by #587")
    ap.add_argument("--no-pack-check", action="store_true", help="tests only")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--dev-rows", type=int, default=256)
    ap.add_argument("--rl-tasks", type=Path)
    ap.add_argument("--rl-ids", type=Path)
    ap.add_argument("--rl-k", type=int, default=8)
    ap.add_argument("--rl-max-new", type=int, default=1536)
    ap.add_argument("--rl-limit", type=int, default=48)
    ap.add_argument("--rl-seconds", type=float, default=0.0)
    ap.add_argument("--steps", type=int, default=243)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--full-lr", type=float, default=1e-4)
    ap.add_argument("--lora-lr", type=float, default=1e-3)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=float, default=32.0)
    # 17 Nov paper-repo DT settings (`agentic-learning-ai-lab/deleting-weights` scripts/train_sft.sh)
    ap.add_argument("--dt-lr", type=float, default=5e-4)
    ap.add_argument("--marker-lr", type=float, default=1e-3)
    ap.add_argument("--dt-targets", default="g5_gate")
    ap.add_argument("--dt-alpha-start", type=float, default=100.0)
    ap.add_argument("--dt-alpha-end", type=float, default=1000.0)
    ap.add_argument("--dt-lambda", type=float, default=1e-5)
    ap.add_argument("--dt-eta", type=float, default=1.0 / 2048.0)
    ap.add_argument("--dt-prior-strength", type=float, default=3.0)
    ap.add_argument("--dt-unseen", default="official", choices=("official", "keep"))
    ap.add_argument("--dt-calib-rows", type=int, default=64)
    ap.add_argument("--max-train-seconds", type=float, default=1200.0)
    ap.add_argument("--deadline-minutes", type=float, default=0.0)
    ap.add_argument("--gen-limit", type=int, default=32)
    ap.add_argument("--gen-max-new", type=int, default=1536)
    ap.add_argument("--gen-seconds", type=float, default=0.0)
    ap.add_argument("--keep-canary-state-dir", type=Path, default=None,
                    help="default off: save DT arm model.safetensors + dt_keep_masks.bin* + SHA256SUMS for Task 11 RL")
    ap.add_argument("--keep-weights-dir", type=Path, default=None,
                    help="default off: save Team 7 Checkpointer run folder(s) for Team 9 watcher")
    ap.add_argument("--keep-weights-arms", type=str, default="dt",
                    help="comma-separated subset of full,lora,dt saved when --keep-weights-dir is set (default: dt)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--origin", default="g5_delivery", choices=("g10_rehearsal", "g5_delivery"))
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
        shutil.rmtree(out / "_inputs", ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
