"""Effort subgroups and length penalty evaluation for RL post-training.

Tests the four effort subgroups (1k, 4k, 16k, 64k) across the 100 fixed prompts
in eval/effort_manifest.json, evaluates the effect of length penalties on reward
distributions and group advantages under the Session 18 objective, and reports
budget obedience, parsing, and functional success rates.

Not the v1 training reward: that is `effort_reward.shape_reward` (see `effort_v1.md`, 3.1). At the default beta of
0.001 the penalty is 0.001 at twice the budget and about 0.009 at ten times, so the group advantage it gives is about
0.0004 against about 0.38 for the ramp. This module is for comparison only. The "median" columns of `--table` use a
median that is the 1,024 generation cap, so they read 0 whatever the label.

Usage:
    python teams/10-post-training/rl/effort_penalty.py
    python teams/10-post-training/rl/effort_penalty.py --beta 0.001 --manifest eval/effort_manifest.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent

EFFORT_BUDGETS: dict[str, int] = {
    "1k": 1024,
    "4k": 4096,
    "16k": 16384,
    "64k": 65536,
}
LABELS = ("1k", "4k", "16k", "64k")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    OBJECTIVE = _load_module("g10_objective_v1", HERE / "objective_v1.py")
except Exception:
    OBJECTIVE = None


def length_penalty(
    token_length: int,
    effort_label: str,
    beta: float = 0.001,
    penalty_type: str = "relative_excess",
) -> float:
    """Calculates length penalty for exceeding requested effort budget.
    
    Zero penalty if token_length <= budget.
    penalty_type:
      - 'relative_excess': beta * max(0, (L - B) / B)
      - 'linear_excess':   beta * max(0, L - B)
    """
    if effort_label not in EFFORT_BUDGETS:
        raise ValueError(f"Unknown effort label {effort_label!r}; valid: {list(EFFORT_BUDGETS)}")
    if token_length < 0:
        raise ValueError("token_length must be non-negative")
    if beta < 0:
        raise ValueError("beta must be non-negative")

    budget = EFFORT_BUDGETS[effort_label]
    excess = max(0, token_length - budget)
    if excess == 0 or beta == 0.0:
        return 0.0

    if penalty_type == "relative_excess":
        return beta * (excess / budget)
    elif penalty_type == "linear_excess":
        return beta * float(excess)
    else:
        raise ValueError(f"Unknown penalty_type {penalty_type!r}")


def penalized_reward(
    base_reward: float,
    token_length: int,
    effort_label: str,
    beta: float = 0.001,
    penalty_type: str = "relative_excess",
    floor: float = 0.0,
) -> float:
    """Adjusts base verifier reward (0.0 to 1.0) with effort length penalty."""
    if not math.isfinite(base_reward):
        raise ValueError("base_reward must be finite")
    pen = length_penalty(token_length, effort_label, beta=beta, penalty_type=penalty_type)
    return max(floor, base_reward - pen)


def evaluate_manifest_slots(manifest_path: Path | str) -> dict:
    """Audits the 100 fixed slots in effort_manifest.json."""
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    slots = data.get("slots", [])
    resolved = [s for s in slots if s.get("status") == "resolved"]
    unavailable = [s for s in slots if s.get("status") != "resolved"]
    by_category = {}
    for s in slots:
        cat = s.get("category", "unknown")
        by_category.setdefault(cat, {"total": 0, "resolved": 0, "unavailable": 0})
        by_category[cat]["total"] += 1
        if s.get("status") == "resolved":
            by_category[cat]["resolved"] += 1
        else:
            by_category[cat]["unavailable"] += 1

    return {
        "total_slots": len(slots),
        "resolved_count": len(resolved),
        "unavailable_count": len(unavailable),
        "categories": by_category,
    }


def analyze_effort_subgroups_from_stage_b(
    results_dir: Path | str,
    beta: float = 0.001,
) -> dict:
    """Analyzes the 440 Stage B cells across the 4 effort subgroups with and without length penalty."""
    p = Path(results_dir)
    pooled_path = p / "stageB_pooled.json"
    if not pooled_path.exists():
        raise FileNotFoundError(f"{pooled_path} does not exist")

    pooled = json.loads(pooled_path.read_text(encoding="utf-8"))
    per_label = pooled.get("per_label", pooled.get("rows", {}))

    subgroup_stats = {}
    for label in LABELS:
        entry = per_label.get(label, {})
        ran = entry.get("ran", 0)
        correct = entry.get("correct", 0)
        within_cap = entry.get("limit", entry.get("within_cap", 0))
        parse_ok = entry.get("parse", entry.get("parse_ok", 0))
        median_tokens = entry.get("generated_tokens_median", entry.get("median_tokens", 0))
        budget = EFFORT_BUDGETS[label]

        # Calculate penalty at median token length
        median_pen = length_penalty(median_tokens, label, beta=beta)
        subgroup_stats[label] = {
            "budget": budget,
            "ran_cells": ran,
            "parse_ok": parse_ok,
            "within_cap": within_cap,
            "raw_correct": correct,
            "raw_pass_rate": (correct / ran) if ran else 0.0,
            "median_tokens": median_tokens,
            "budget_obeyed": median_tokens <= budget,
            "median_length_penalty": median_pen,
            "net_penalized_reward": max(0.0, (correct / ran) - median_pen) if ran else 0.0,
        }

    return {
        "results_dir": str(p),
        "beta": beta,
        "subgroups": subgroup_stats,
    }


def format_subgroups_table(analysis: dict) -> str:
    """Generates markdown table of effort subgroups and length penalty."""
    lines = [
        "| Effort Subgroup | Token Budget | Ran Cells | Parse OK | Within Cap (1024) | Raw Correct | Pass@1 | Median Tokens | Budget Obeyed | Median Penalty (β=0.001) | Net Reward |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|",
    ]
    for label, s in analysis["subgroups"].items():
        obeyed = "yes" if s["budget_obeyed"] else "no"
        lines.append(
            f"| **{label}** | {s['budget']:,} | {s['ran_cells']} | {s['parse_ok']} | {s['within_cap']} | "
            f"{s['raw_correct']} | {s['raw_pass_rate']:.1%} | {s['median_tokens']} | {obeyed} | "
            f"-{s['median_length_penalty']:.4f} | {s['net_penalized_reward']:.4f} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=TEAM / "eval" / "effort_manifest.json",
        help="Path to effort_manifest.json",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=TEAM / "results" / "effort_stageB_qwen_2026-11-12",
        help="Directory holding stageB_pooled.json",
    )
    parser.add_argument("--beta", type=float, default=0.001, help="Length penalty weight")
    parser.add_argument("--table", action="store_true", help="Print formatted markdown table")
    args = parser.parse_args()

    manifest_audit = evaluate_manifest_slots(args.manifest)
    subgroup_analysis = analyze_effort_subgroups_from_stage_b(args.results_dir, beta=args.beta)

    if args.table:
        print(f"### Manifest Audit (100 Slots)\n")
        print(f"Total: {manifest_audit['total_slots']}, Resolved: {manifest_audit['resolved_count']}, Unavailable: {manifest_audit['unavailable_count']}\n")
        print(format_subgroups_table(subgroup_analysis))
    else:
        out = {
            "manifest_audit": manifest_audit,
            "effort_analysis": subgroup_analysis,
        }
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
