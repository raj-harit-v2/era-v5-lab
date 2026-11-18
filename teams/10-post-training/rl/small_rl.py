"""Small RL loop: code-verifier rewards, then the Session 18 objective.

Local mode trains a two-completion policy on one existing code task. The
completions are scored by rl/verifier.py. The open-model run is the job request.
This script does not download a model.

    python teams/10-post-training/rl/small_rl.py --steps 20 --seed 0
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


OBJECTIVE = _load("g10_objective_v1_for_small_rl", "objective_v1.py")


def log_softmax(logits: list[float]) -> tuple[list[float], list[float]]:
    peak = max(logits)
    shifted = [math.exp(value - peak) for value in logits]
    total = sum(shifted)
    probs = [value / total for value in shifted]
    return [math.log(prob) for prob in probs], probs


def update_policy(
    logits: list[float],
    chosen: list[int],
    rewards: list[float],
    old_logprobs: list[float],
    lr: float,
    epsilon: float = OBJECTIVE.EPSILON,
) -> tuple[list[float], float, bool]:
    """One group update. Returns new logits, the objective loss, and whether the group was kept."""
    if not (len(chosen) == len(rewards) == len(old_logprobs)):
        raise ValueError("chosen, rewards, and old_logprobs must be the same length")
    mean_reward = sum(rewards) / len(rewards)
    advantages = OBJECTIVE.group_advantage(rewards)
    if advantages is None:
        return list(logits), 0.0, False
    logprobs, probs = log_softmax(logits)
    rollouts = []
    masked_advantage = []
    for reward, advantage, index, old in zip(rewards, advantages, chosen, old_logprobs):
        logprob = logprobs[index]
        ratio = math.exp(logprob - old)
        rollouts.append(OBJECTIVE.Rollout(reward, (logprob,), (ratio,)))
        masked_advantage.append((advantage, index, OBJECTIVE.trust_region_mask([ratio], epsilon)[0]))
    result = OBJECTIVE.objective_v1([rollouts], epsilon=epsilon)
    grad = [0.0] * len(logits)
    tokens = len(chosen)
    for advantage, index, bit in masked_advantage:
        for axis, prob in enumerate(probs):
            dlogp = (1.0 if axis == index else 0.0) - prob
            grad[axis] += (-bit * advantage / tokens) * dlogp
    return [value - lr * part for value, part in zip(logits, grad)], result.loss, True


def sample_group(probs: list[float], group_size: int, rng: random.Random) -> list[int]:
    chosen = []
    for _ in range(group_size):
        draw = rng.random()
        acc = 0.0
        pick = len(probs) - 1
        for index, prob in enumerate(probs):
            acc += prob
            if draw <= acc:
                pick = index
                break
        chosen.append(pick)
    return chosen


def run_local(rewards: list[float], steps: int, group_size: int, lr: float, seed: int) -> dict:
    """Train on a fixed reward for each completion. rewards[i] is completion i."""
    if len(rewards) < 2:
        raise ValueError("the local policy needs two completions")
    rng = random.Random(seed)
    logits = [0.0] * len(rewards)
    curve = []
    for _ in range(steps):
        _, probs = log_softmax(logits)
        chosen = sample_group(probs, group_size, rng)
        logprobs, _ = log_softmax(logits)
        old = [logprobs[index] for index in chosen]
        group_rewards = [rewards[index] for index in chosen]
        logits, loss, kept = update_policy(logits, chosen, group_rewards, old, lr)
        curve.append({
            "mean_reward": sum(group_rewards) / len(group_rewards),
            "loss": loss,
            "kept": kept,
        })
    _, probs = log_softmax(logits)
    return {"curve": curve, "probs": probs, "rewards": rewards}


def _fence(code: str) -> str:
    return "```python\n" + code.strip() + "\n```\n"


def score_task(task_id: str) -> list[float]:
    """Score the reference solution and one wrong solution. Returns [correct, wrong]."""
    verifier = _load("g10_verifier_for_small_rl", "verifier.py")
    task_dir = HERE / "tasks" / task_id
    correct = _fence((task_dir / "reference.py").read_text(encoding="utf-8"))
    entry = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))["entry_point"]
    wrong = _fence(f"def {entry}(*args, **kwargs):\n    return None\n")
    correct_score = verifier.reward(task_dir, correct, sandbox="process")["reward"]
    wrong_score = verifier.reward(task_dir, wrong, sandbox="process")["reward"]
    return [float(correct_score), float(wrong_score)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="next_business_day")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="local-categorical")
    args = parser.parse_args()
    if args.model != "local-categorical":
        raise SystemExit("open-model sampling is the job request; this machine runs --model local-categorical")
    rewards = score_task(args.task)
    report = run_local(rewards, args.steps, args.group_size, args.lr, args.seed)
    kept = [row["mean_reward"] for row in report["curve"]]
    report["task"] = args.task
    report["model"] = args.model
    report["reward_first"] = kept[0]
    report["reward_last"] = kept[-1]
    report["prob_correct"] = report["probs"][0]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
