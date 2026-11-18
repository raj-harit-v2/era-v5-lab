"""CPU-only guards for tool-call decoding through HF and G10 codec fixtures.

No real model/tokenizer performance claim is made by these fixtures.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent

BODY = '<|tool_call|>\n{"name":"fixture_tool","arguments":{}}\n<|/tool_call|>'


def tasks_module():
    spec = importlib.util.spec_from_file_location("g10_tool_use_tasks_under_test", HERE / "tasks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeHFTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return list(messages[-1]["content"].encode("utf-8"))

    def decode(self, completion, skip_special_tokens=False):
        text = bytes(completion).decode("utf-8")
        if skip_special_tokens:
            for token in ("<|tool_call|>", "<|/tool_call|>", "<|im_end|>", "<|endoftext|>"):
                text = text.replace(token, "")
        return text


def test_hf_tool_use_decoding_preserves_the_call_markers():
    tasks = tasks_module()
    task = tasks.RewardEnvTask(FakeHFTokenizer(), [("tool_call/a", "prompt a")], [("tool_call/b", "prompt b")])
    assert task.decode(list(BODY.encode("utf-8"))) == BODY


def test_hf_tool_use_reward_receives_only_the_completion_with_its_markers():
    tasks = tasks_module()
    seen = []

    def reward_fn(env_id, completion):
        seen.append((env_id, completion))
        return float(completion == BODY), {}

    task = tasks.RewardEnvTask(FakeHFTokenizer(), [("tool_call/a", "private prompt")], [], reward_fn)
    assert task.reward(task.train[0], list(BODY.encode("utf-8"))) == 1.0
    assert seen == [("tool_call/a", BODY)]


def test_g10_codec_path_keeps_its_existing_completion_decoder():
    tasks = tasks_module()

    class FakeG10Codec(FakeHFTokenizer):
        def decode_completion(self, completion):
            return BODY

    task = tasks.RewardEnvTask(FakeG10Codec(), [("tool_call/a", "prompt a")], [])
    assert task.decode([100, 101]) == BODY


def test_hf_non_tool_decoding_keeps_legacy_special_token_handling():
    tasks = tasks_module()
    task = tasks.RewardEnvTask(FakeHFTokenizer(), [("code/a", "prompt a")], [])
    assert task.decode(list(BODY.encode("utf-8"))) == '\n{"name":"fixture_tool","arguments":{}}\n'


def test_hf_mixed_environments_select_decoding_per_reward_call():
    tasks = tasks_module()
    seen = []

    def reward_fn(env_id, completion):
        seen.append((env_id, completion))
        return 1.0, {}

    task = tasks.RewardEnvTask(FakeHFTokenizer(), [("code/a", "prompt a"), ("tool_call/b", "prompt b")], [], reward_fn)
    for prompt in task.train:
        task.reward(prompt, list(BODY.encode("utf-8")))
    assert seen == [("code/a", '\n{"name":"fixture_tool","arguments":{}}\n'), ("tool_call/b", BODY)]
