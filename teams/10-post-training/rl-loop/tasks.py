"""Where prompts and rewards come from.

ToyTask       Pure token arithmetic for smoke tests (no text, no data): the prompt is random token ids.
              rule "exact": reward 1 if the first completion token equals (last prompt token + offset) mod vocab.
                  A random model starts near 1/vocab, so the loop must learn a real mapping. For small vocabs.
              rule "parity": reward 1 if the first completion token has the same parity as the last prompt token.
                  A random model starts near 0.5, so every step has signal even with a 50k vocab (GPU measurement).
              rule "even": reward 1 if the first completion token id is even, whatever the prompt. Parity of the last
                  prompt token is an arbitrary function of a token id (a model with no per-id input rows, as in G5's
                  KE2 byte-code input, cannot generalise it to unseen prompts), so "parity" can only be memorised
                  on the training prompts; "even" is a prompt-independent output preference that held-out prompts
                  share. Starts near 0.5 for a model with a near-uniform first-token distribution.
              It proves the loop learns; it is not training data for any real model.
RewardEnvTask Real environments through one reward function `reward_fn(env_id, text) -> (score, info)`, by default
              rl/reward.py (code tasks and SWE envs). Prompts are rendered with the tokenizer's chat template.
              Which env_ids may be used for training is TSAI's call (see README).
"""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path
from typing import Callable

RL_DIR = Path(__file__).resolve().parents[1] / "rl"


class ToyTask:
    def __init__(self, vocab: int, prompt_len: int = 4, offset: int = 3, n_train: int = 256, n_heldout: int = 64,
                 seed: int = 0, low: int = 0, rule: str = "exact"):
        if rule not in ("exact", "parity", "even"):
            raise ValueError(f"unknown toy rule {rule!r}")
        self.rule = rule
        rng = random.Random(seed)
        self.vocab, self.offset, self.low = vocab, offset, low

        def make(n):
            return [[rng.randrange(low, vocab) for _ in range(prompt_len)] for _ in range(n)]

        self.train, self.heldout = make(n_train), make(n_heldout)

    def target(self, prompt: list[int]) -> int:
        return self.low + (prompt[-1] - self.low + self.offset) % (self.vocab - self.low)

    def reward(self, prompt: list[int], completion: list[int]) -> float:
        if not completion:
            return 0.0
        if self.rule == "parity":
            return float(completion[0] % 2 == prompt[-1] % 2)
        if self.rule == "even":
            return float(completion[0] % 2 == 0)
        return float(completion[0] == self.target(prompt))


def default_reward_fn() -> Callable[[str, str], tuple[float, dict]]:
    """rl/reward.py's reward(env_id, output), loaded by path (it arrives with the reward-wrapper PR)."""
    path = RL_DIR / "reward.py"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; pass reward_fn=... or merge the reward-wrapper PR first")
    spec = importlib.util.spec_from_file_location("g10_rl_reward", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.reward


class RewardEnvTask:
    """train/heldout are lists of (env_id, prompt_text). The completion is decoded and scored by reward_fn."""

    def __init__(self, tokenizer, train: list[tuple[str, str]], heldout: list[tuple[str, str]],
                 reward_fn: Callable[[str, str], tuple[float, dict]] | None = None):
        self.tok = tokenizer
        self.reward_fn = reward_fn or default_reward_fn()
        self._items = {}
        self.train = [self._encode(e, p) for e, p in train]
        self.heldout = [self._encode(e, p) for e, p in heldout]

    def _encode(self, env_id: str, prompt: str) -> list[int]:
        if hasattr(self.tok, "encode_prompt"):  # G10 codec (team5_adapter.G10Codec): chat_template.jinja prefix
            ids = [int(x) for x in self.tok.encode_prompt(prompt)]
        else:  # Hugging Face tokenizer
            msgs = [{"role": "user", "content": prompt}]
            ids = self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
            ids = [int(x) for x in (ids["input_ids"] if hasattr(ids, "keys") else ids)]  # BatchEncoding is not a dict
        key = tuple(ids)
        if key in self._items:  # one prompt must map to one env id, and no prompt may sit in both splits
            raise ValueError(f"prompt for {env_id!r} encodes identically to {self._items[key]!r}; "
                             "duplicate or colliding task (check the train/heldout split)")
        self._items[key] = env_id
        return ids

    def decode(self, completion: list[int], env_id: str | None = None) -> str:
        if hasattr(self.tok, "decode_completion"):  # keeps marker text, cuts after the first stop id
            return self.tok.decode_completion(completion)
        # Tool-use rewards inspect atomic marker text. Other environments retain
        # their existing decoding, including in a mixed-environment batch.
        ids = [env_id] if env_id is not None else self._items.values()
        keep_markers = any(e.partition("/")[0] in {"tool_call", "tool_use"} for e in ids)
        return self.tok.decode(completion, skip_special_tokens=not keep_markers)

    def reward(self, prompt: list[int], completion: list[int]) -> float:
        env_id = self._items[tuple(prompt)]
        score, _ = self.reward_fn(env_id, self.decode(completion, env_id=env_id))
        return float(score)


def code_task_prompts(task_ids: list[str]) -> list[tuple[str, str]]:
    """(env_id, prompt) pairs for rl/tasks/<id>. Evaluation only until TSAI rules on Claude-written task text."""
    return [(f"code/{t}", (RL_DIR / "tasks" / t / "prompt.md").read_text(encoding="utf-8")) for t in task_ids]
